import sys
import os
import comtypes.client

def convert_pptx_to_pdf():
    # Paths
    ppt_path = r"C:\Users\hp\OneDrive\Desktop\[PUB] India_runs_data_and_ai_challenge\IOO_AI_Ranking_System.pptx"
    pdf_path = r"C:\Users\hp\OneDrive\Desktop\[PUB] India_runs_data_and_ai_challenge\IOO_AI_Ranking_System.pdf"

    if not os.path.exists(ppt_path):
        print(f"Error: {ppt_path} does not exist.")
        return

    # Delete existing pdf if any to prevent overwrite errors
    if os.path.exists(pdf_path):
        try:
            os.remove(pdf_path)
        except Exception as e:
            print(f"Could not remove existing PDF: {e}")

    print("Initializing PowerPoint COM client...")
    try:
        powerpoint = comtypes.client.CreateObject("PowerPoint.Application")
        # Keep window hidden if possible (or minimize)
        powerpoint.Visible = True # PowerPoint requires Visible to load presentations via API
    except Exception as e:
        print(f"Failed to create PowerPoint COM client: {e}")
        return

    try:
        print(f"Opening presentation: {ppt_path}")
        deck = powerpoint.Presentations.Open(ppt_path, WithWindow=False)
        # FormatType for PDF is 32
        print(f"Saving presentation as PDF: {pdf_path}")
        deck.SaveAs(pdf_path, 32)
        deck.Close()
        print("Conversion successful!")
    except Exception as e:
        print(f"Error during conversion: {e}")
    finally:
        powerpoint.Quit()

if __name__ == "__main__":
    convert_pptx_to_pdf()
