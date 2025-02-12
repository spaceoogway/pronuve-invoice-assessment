import streamlit as st


def inject_logo():
    # Simple circle logo using a div
    st.markdown(
        """
        <div style="display: flex; align-items: center; justify-content: center; margin: 10px auto;">
            <svg width="40" height="40" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path d="M17.1 19.59a6.34 6.34 0 0 1-4.54 1.91H12V4.23l5.47 6.58a6.56 6.56 0 0 1-.37 8.78z" 
                      fill="none" stroke="#0073e6" stroke-width="1.73" stroke-miterlimit="10"/>
                <path d="M12 2.5v17.27h-.56a6.36 6.36 0 0 1-4.54-1.91 6.55 6.55 0 0 1-.37-8.78z" 
                      fill="none" stroke="#0073e6" stroke-width="1.73" stroke-miterlimit="10"/>
                <path d="M12 12.86l3.89-3.88M12 18.91l6.48-6.48" 
                      fill="none" stroke="#0073e6" stroke-width="1.73" stroke-miterlimit="10"/>
            </svg>
            <span style="color: #0073e6; font-family: Arial, sans-serif; font-size: 20px; font-weight: bold; margin-left: 10px;">pronuve</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def inject_css():
    st.markdown(
        """
        <style>
        /* Adaptive styling using CSS variables */
        :root {
           --card-bg-metric: #e8f4f8;
           --card-text-metric: #000000;
           --card-bg-default: #ffffff;
           --card-text-default: #000000;
        }
        @media (prefers-color-scheme: dark) {
           :root {
             --card-bg-metric: #555555;
             --card-text-metric: #ffffff;
             --card-bg-default: #444444;
             --card-text-default: #ffffff;
           }
        }
        
        /* Hide default Streamlit UI elements */
        [data-testid="collapsedControl"] { display: none; }
        section[data-testid="stSidebar"] { display: none; }
        #MainMenu { visibility: hidden; }
        header { visibility: hidden; }
        footer { visibility: hidden; }
        .block-container { padding-top: 0rem; padding-bottom: 0rem; }
        
        /* Card styling for st.metric widgets */
        div[data-testid="stMetric"] {
           background-color: var(--card-bg-metric) !important;
           color: var(--card-text-metric) !important;
           border-radius: 10px;
           padding: 20px;
           margin-bottom: 10px;
           box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }
        
        /* Card styling for Altair charts */
        div[data-testid="stAltairChart"] {
           background-color: var(--card-bg-default) !important;
           color: var(--card-text-default) !important;
           border-radius: 10px;
           padding: 20px;
           margin-top: 20px;
           box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }
        
        /* Card styling for DataFrame containers */
        div[data-testid="stDataFrameContainer"] {
           background-color: var(--card-bg-default) !important;
           color: var(--card-text-default) !important;
           border-radius: 10px;
           padding: 20px;
           margin-top: 20px;
           box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
