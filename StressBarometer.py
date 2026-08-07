# ============================================================
# DODATNI IMPORT ZA OMREŽNI DIAGRAM
# ============================================================

import plotly.graph_objects as go
import numpy as np


# ============================================================
# OMREŽNI DIAGRAM - HIERARHIČNA MREŽA
# ============================================================

def create_network_graph(
    df,
    columns,
    top_categories=6,
    top_keywords=5
):

    nodes = []
    edges = []
    node_type = {}

    center_nodes = {
        columns[0]: "PF",
        columns[1]: "SF",
        columns[2]: "PR"
    }


    # --------------------------------------------------------
    # CENTRALNA VOZLIŠČA
    # --------------------------------------------------------

    for col, short in center_nodes.items():

        nodes.append(short)

        node_type[short] = "center"



    # --------------------------------------------------------
    # KATEGORIJE IN KLJUČNE BESEDE
    # --------------------------------------------------------

    for col, short in center_nodes.items():

        category_counter = Counter()


        for value in df[col].dropna():

            keywords = clean_and_tokenize(value)

            categories = classify_keywords(
                keywords
            )

            category_counter.update(
                categories
            )


        for category, freq in category_counter.most_common(
            top_categories
        ):

            category_node = (
                f"{category}"
            )


            if category_node not in nodes:

                nodes.append(
                    category_node
                )

                node_type[
                    category_node
                ] = "category"


            edges.append(
                (
                    short,
                    category_node,
                    freq
                )
            )


            keyword_counter = Counter()


            for value in df[col].dropna():

                words = clean_and_tokenize(
                    value
                )


                for word in words:

                    for key in CATEGORIES_MAP[category]:

                        if word.startswith(
                            key.lower()[:5]
                        ):

                            keyword_counter.update(
                                [word]
                            )


            for word, wf in keyword_counter.most_common(
                top_keywords
            ):

                if word not in nodes:

                    nodes.append(
                        word
                    )

                    node_type[word] = "keyword"


                edges.append(
                    (
                        category_node,
                        word,
                        wf
                    )
                )



    # --------------------------------------------------------
    # POZICIJE VOZLIŠČ
    # --------------------------------------------------------

    positions = {}


    positions["PF"] = (-2,0)
    positions["SF"] = (0,0)
    positions["PR"] = (2,0)



    category_nodes = [
        n for n in nodes
        if node_type[n]=="category"
    ]


    for i,n in enumerate(category_nodes):

        angle = (
            2*np.pi*i /
            max(len(category_nodes),1)
        )

        positions[n] = (
            np.cos(angle)*3,
            np.sin(angle)*3
        )



    keyword_nodes = [
        n for n in nodes
        if node_type[n]=="keyword"
    ]


    for i,n in enumerate(keyword_nodes):

        angle = (
            2*np.pi*i /
            max(len(keyword_nodes),1)
        )

        positions[n] = (
            np.cos(angle)*5,
            np.sin(angle)*5
        )



    # --------------------------------------------------------
    # POVEZAVE
    # --------------------------------------------------------

    edge_x=[]
    edge_y=[]


    for a,b,w in edges:

        if a in positions and b in positions:

            x0,y0 = positions[a]
            x1,y1 = positions[b]

            edge_x += [
                x0,x1,None
            ]

            edge_y += [
                y0,y1,None
            ]



    edge_trace = go.Scatter(

        x=edge_x,
        y=edge_y,

        mode="lines",

        line=dict(
            width=1
        ),

        hoverinfo="none"

    )



    # --------------------------------------------------------
    # VOZLIŠČA
    # --------------------------------------------------------

    node_x=[]
    node_y=[]
    labels=[]


    for n in nodes:

        if n in positions:

            x,y = positions[n]

            node_x.append(x)
            node_y.append(y)

            labels.append(n)



    node_trace = go.Scatter(

        x=node_x,
        y=node_y,

        mode="markers+text",

        text=labels,

        textposition="top center",

        marker=dict(
            size=25
        )

    )



    fig = go.Figure(
        data=[
            edge_trace,
            node_trace
        ]
    )


    fig.update_layout(

        title=
        "🕸️ Hierarhični omrežni prikaz stresnih struktur",

        height=750,

        showlegend=False,

        xaxis=dict(
            visible=False
        ),

        yaxis=dict(
            visible=False
        )

    )


    return fig
	
# ========================================================
# MATEMATIČNA FORMULA
# ========================================================

# ========================================================
# OMREŽNA ANALIZA STRESNIH STRUKTUR
# ========================================================

st.divider()

st.header(
    "🕸️ Omrežni diagram povezanosti dejavnikov"
)


st.markdown(
"""
Interaktivni prikaz prikazuje hierarhične povezave:

**PF / SF / PR → klasifikacijska enota → ključni pojmi**

- PF = pozitivni zaščitni dejavniki
- SF = stresni dejavniki
- PR = predlogi izboljšav

Velikost mreže je odvisna od števila zaznanih povezav.
"""
)


network_mode = st.selectbox(
    "🔧 Globina omrežnega prikaza",
    [
        "Kategorije + ključne besede",
        "Samo kategorije"
    ]
)



if network_mode == "Samo kategorije":

    network_fig = create_network_graph(
        df,
        target_cols,
        top_categories=8,
        top_keywords=0
    )

else:

    network_fig = create_network_graph(
        df,
        target_cols,
        top_categories=6,
        top_keywords=5
    )


st.plotly_chart(
    network_fig,
    use_container_width=True
)



# ========================================================
# OMREŽNA STATISTIKA
# ========================================================

st.subheader(
    "📡 Strukturna statistika omrežja"
)


network_col1, network_col2, network_col3 = st.columns(3)


with network_col1:

    st.metric(
        "Osrednje ravni",
        "PF / SF / PR"
    )


with network_col2:

    total_categories = 0

    for col in target_cols[:3]:

        for value in df[col].dropna():

            total_categories += len(
                classify_keywords(
                    clean_and_tokenize(value)
                )
            )


    st.metric(
        "Zaznane povezave",
        total_categories
    )


with network_col3:

    st.metric(
        "Hierarhični nivoji",
        "3"
    )



# ========================================================
# TOP POVEZAVE
# ========================================================

st.subheader(
    "🔗 Najmočnejše vsebinske povezave"
)


network_edges = []


for col in target_cols[:3]:

    if col == target_cols[0]:

        source = "PF"

    elif col == target_cols[1]:

        source = "SF"

    else:

        source = "PR"



    counter = Counter()


    for value in df[col].dropna():

        cats = classify_keywords(
            clean_and_tokenize(value)
        )

        counter.update(
            cats
        )


    for category, freq in counter.most_common(10):

        network_edges.append(
            {
                "Izvor": source,
                "Cilj": category,
                "Moč povezave": freq
            }
        )



if network_edges:

    edge_df = pd.DataFrame(
        network_edges
    )


    st.dataframe(
        edge_df,
        use_container_width=True,
        hide_index=True
    )



    fig_network_bar = px.bar(
        edge_df.sort_values(
            "Moč povezave"
        ),
        x="Moč povezave",
        y="Cilj",
        color="Izvor",
        orientation="h",
        text="Moč povezave",
        title="Najpogostejše hierarhične povezave"
    )


    fig_network_bar.update_layout(
        height=450,
        yaxis_title="",
        xaxis_title="Število povezav"
    )


    fig_network_bar.update_traces(
        textposition="outside"
    )


    st.plotly_chart(
        fig_network_bar,
        use_container_width=True
    )


else:

    st.info(
        "Ni dovolj podatkov za omrežno analizo."
    )
	
	# ============================================================
# DODATNA FUNKCIJA - IZVOZ OMREŽNIH PODATKOV
# ============================================================

def export_network_data(
    df,
    columns
):

    network_data = []


    for col in columns[:3]:

        if col == columns[0]:

            source = "PF"

        elif col == columns[1]:

            source = "SF"

        else:

            source = "PR"


        category_counter = Counter()


        for value in df[col].dropna():

            keywords = clean_and_tokenize(
                value
            )

            categories = classify_keywords(
                keywords
            )

            category_counter.update(
                categories
            )


        for category, freq in category_counter.items():

            network_data.append(
                {
                    "Vir": source,
                    "Kategorija": category,
                    "Frekvenca": freq
                }
            )


    return pd.DataFrame(
        network_data
    )



# ============================================================
# DODATNA VIZUALIZACIJA - STRUKTURNA MREŽA
# ============================================================

def create_simple_network_summary(
    df,
    columns
):

    summary = []


    labels = [
        "PF",
        "SF",
        "PR"
    ]


    for i,col in enumerate(columns[:3]):

        counter = Counter()


        for value in df[col].dropna():

            categories = classify_keywords(
                clean_and_tokenize(value)
            )

            counter.update(
                categories
            )


        for cat,freq in counter.most_common(5):

            summary.append(
                {
                    "Nivo 1": labels[i],
                    "Nivo 2": cat,
                    "Moč": freq
                }
            )


    return pd.DataFrame(
        summary
    )



# ============================================================
# DODATNI IZVOZ V GLAVNEM DELU APLIKACIJE
# ============================================================

# Vstavite pred matematično formulo ali pred konec main():

st.divider()

st.header(
    "💾 Izvoz omrežne analize"
)


network_export_df = export_network_data(
    df,
    target_cols
)


if not network_export_df.empty:


    csv_network = (
        network_export_df
        .to_csv(
            index=False
        )
        .encode(
            "utf-8"
        )
    )


    st.download_button(

        label=
        "⬇️ Prenesi omrežne podatke CSV",

        data=csv_network,

        file_name=
        "stress_network_analysis.csv",

        mime=
        "text/csv"

    )


    st.dataframe(
        network_export_df,
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# ZAKLJUČEK APLIKACIJE
# ============================================================


st.divider()

st.caption(
"""
Stress Analysis Pro
|
Petričeva klasifikacija stresnih dejavnikov
|
Hierarhični omrežni model PF-SF-PR
"""
)



# ============================================================
# ZAGON
# ============================================================

if __name__ == "__main__":

    main()



