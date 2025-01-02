import csv

def remove_empty_rows(input_file: str, output_file: str):
    """
    Remove empty rows from a CSV file.
    
    Args:
        input_file (str): Path to the input CSV file.
        output_file (str): Path to the output CSV file without empty rows.
    """
    with open(input_file, mode='r', newline='') as infile, open(output_file, mode='w', newline='') as outfile:
        reader = csv.reader(infile)
        writer = csv.writer(outfile)
        
        row_count = 0
        empty_row_count = 0
        
        for row in reader:
            row_count += 1
            # Check if the row has any non-empty cells
            if any(cell.strip() for cell in row):
                writer.writerow(row)
            else:
                empty_row_count += 1
        
        print(f"Processed {row_count} rows.")
        print(f"Removed {empty_row_count} empty rows.")
        print(f"Cleaned CSV saved to: {output_file}")


# Example usage
if __name__ == "__main__":
    input_csv = 'professor_paper_counts_manual.csv'  # Replace with your input CSV file path
    output_csv = 'professor_paper_counts_manual_clean.csv'  # Replace with desired output file path
    
    remove_empty_rows(input_csv, output_csv)
