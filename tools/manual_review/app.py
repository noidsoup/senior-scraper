#!/usr/bin/env python3
import streamlit as st
import pandas as pd
import os
import sys
import requests
from urllib.parse import quote

# Add project root to path so we can import from tools
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from tools.manual_review.lib import (
    load_base_data,
    load_progress as lib_load_progress,
    save_progress as lib_save_progress,
    upsert_decision,
    export_wp_import as lib_export,
)

DATA_FILE = 'organized_csvs/Listings-Export-2025-September-10-1916.csv'
PROGRESS_FILE = 'manual_review_progress.csv'
EXPORT_FILE = 'manual_review_wp_import.csv'

st.set_page_config(page_title='Seniorly Manual Review', layout='wide')

@st.cache_data
def load_data():
    return load_base_data(DATA_FILE)

def load_progress():
    return lib_load_progress(PROGRESS_FILE)


def save_progress(progress_df: pd.DataFrame):
    lib_save_progress(PROGRESS_FILE, progress_df)


def export_wp_import(progress_df: pd.DataFrame, base_df: pd.DataFrame):
    out = lib_export(progress_df, base_df)
    out.to_csv(EXPORT_FILE, index=False)
    return out

def create_capacity_search_link(title: str, location: str = ""):
    """Create Google search link asking about big community vs small home"""
    query = f"is {title} {location} big community or small home assisted living".strip()
    encoded_query = quote(query)
    url = f"https://www.google.com/search?q={encoded_query}"
    return url

st.title('Seniorly Manual Review (Home vs Community)')

# Sidebar controls
with st.sidebar:
    st.header('Controls')
    df = load_data()
    prog = load_progress()
    # Only count Home/Community as "reviewed" - Unclear stays in remaining
    reviewed_decisions = prog[prog['Decision'].isin(['Home', 'Community'])]
    done_ids = set(reviewed_decisions['ID'].tolist())

    st.markdown(f"Total listings: **{len(df)}**")
    st.markdown(f"Reviewed (Home/Community): **{len(done_ids)}**")
    st.markdown(f"Remaining: **{len(df) - len(done_ids)}**")
    # Progress info only

    view_mode = st.radio('View:', ['Only remaining', 'All listings'], index=0)
    show_only_remaining = (view_mode == 'Only remaining')
    
    # Add search functionality
    search_term = st.text_input('🔍 Search by name or ID:', placeholder='e.g. Marigold or 12345')

    if st.button('Export WP Import CSV'):
        out = export_wp_import(prog, df)
        st.success(f'Exported {len(out)} corrections to {EXPORT_FILE}')
        st.download_button('Download WP Import CSV', data=out.to_csv(index=False), file_name='WP_IMPORT_from_manual_review.csv', mime='text/csv')

# Filtering
view = df.copy()
if show_only_remaining:
    view = view[~view['ID'].isin(done_ids)]

# Apply search filter
if search_term:
    search_lower = search_term.lower()
    # Search in title, ID, or location
    search_mask = (
        view['Title'].str.lower().str.contains(search_lower, na=False) |
        view['ID'].astype(str).str.contains(search_lower, na=False) |
        view['Locations'].str.lower().str.contains(search_lower, na=False)
    )
    view = view[search_mask]

# Pagination
page_size = st.sidebar.selectbox('Rows per page', [10,25,50,100], index=1)
page = st.sidebar.number_input('Page', min_value=1, value=1)
start = (page-1)*page_size
end = start + page_size
subset = view.iloc[start:end]

st.markdown('---')

if subset.empty:
    st.info('No rows to show with current filters. Adjust filters or pagination.')
else:
    def upsert_and_save(prog_df: pd.DataFrame, row_id, decision_value, note_value) -> pd.DataFrame:
        updated = upsert_decision(prog_df, row_id, decision_value, note_value)
        save_progress(updated)
        st.cache_data.clear()
        return updated


    for _, row in subset.iterrows():
        with st.container(border=True):
            st.subheader(f"{row['Title']}")
            cols = st.columns([3,2,3,2,2])
            
            # Column 0: Image and Info
            with cols[0]:
                # Try to get image from export data
                image_url = None
                image_source = "none"
                
                # Priority order: Image Featured -> Image URL -> photos -> Attachment URL
                if pd.notna(row.get('Image Featured', '')) and row.get('Image Featured', '').strip():
                    image_url = row['Image Featured'].strip()
                    image_source = "Image Featured"
                elif pd.notna(row.get('Image URL', '')) and row.get('Image URL', '').strip():
                    image_url = row['Image URL'].strip()
                    image_source = "Image URL"
                elif pd.notna(row.get('photos', '')) and row.get('photos', '').strip():
                    # photos might be a comma-separated list, take the first one
                    photos = str(row['photos']).strip()
                    if photos and photos != 'nan':
                        image_url = photos.split(',')[0].strip()
                        image_source = "photos"
                elif pd.notna(row.get('Attachment URL', '')) and row.get('Attachment URL', '').strip():
                    image_url = row['Attachment URL'].strip()
                    image_source = "Attachment URL"
                
                if image_url and image_url.startswith('http'):
                    try:
                        st.image(image_url, width=300)
                    except Exception as e:
                        st.write("📷 Image failed to load")
                else:
                    st.write("📷 No image available")
                
                # Info below image
                st.write(f"**ID:** {row['ID']}")
                if 'Locations' in row:
                    st.write(f"**City:** {row['Locations']}")
                if 'States' in row:
                    st.write(f"**State:** {row['States']}")
                st.caption(f"Source: {image_source}")
                
                # Action button
                if row.get('URL'):
                    st.link_button('🔗 Open Seniorly', row['URL'])
            
            # Column 1: Empty (removed duplicate info)
            with cols[1]:
                st.write("")  # Keep for spacing
            
            # Column 2: Research link
            with cols[2]:
                location = f"{row.get('Locations', '')} {row.get('States', '')}".strip()
                search_url = create_capacity_search_link(row['Title'], location)
                
                st.write("***slaps top of senior listing***")
                st.link_button("🔍 How many seniors can they fit in there?", search_url)
            # Column 3: Decision
            with cols[3]:
                st.write('**Decision:**')
                key = f"decision_{row['ID']}"
                current = prog.loc[prog['ID']==row['ID'],'Decision']
                current_val = current.iloc[0] if not current.empty else None
                
                # Get current notes for auto-save
                note_key = f"note_{row['ID']}"
                current_note = prog.loc[prog['ID']==row['ID'],'Notes']
                note_val = current_note.iloc[0] if not current_note.empty else ''
                
                decision = st.radio('Decision', ['Home','Community','Unclear'], index=['Home','Community','Unclear'].index(current_val) if current_val in ['Home','Community','Unclear'] else 2, horizontal=True, key=key, label_visibility='collapsed')
                
                # Auto-save when radio selection changes
                if decision != current_val:
                    prog = upsert_and_save(prog, row['ID'], decision, note_val)
                    st.success('Auto-saved!')
                    st.rerun()
                    
                st.caption('Auto-saves when you change selection')
                
            # Column 4: Notes & Status
            with cols[4]:
                notes = st.text_input('Notes (optional)', value=note_val, key=note_key)
                # Auto-save notes when they change
                if notes != note_val:
                    prog = upsert_and_save(prog, row['ID'], decision, notes)
                    st.success('Notes saved!')
                    st.rerun()
                
                # Show current status
                is_reviewed = row['ID'] in done_ids
                status = 'Reviewed' if is_reviewed else 'Not reviewed'
                st.write(f'**Status:** {status}')

st.markdown('---')
st.caption('Progress is auto-saved to manual_review_progress.csv and can be resumed anytime. Use Export to produce the WP import file from your decisions.')
