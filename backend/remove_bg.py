from PIL import Image

def remove_background(input_path, output_path):
    img = Image.open(input_path).convert("RGBA")
    datas = img.getdata()
    
    new_data = []
    for item in datas:
        # The checkerboard is usually white and gray. We check if r,g,b are close and > 200
        # White is 255,255,255. Gray in checkerboard is usually ~204,204,204.
        # So we threshold grays and whites
        r, g, b, a = item
        # If it's grayish/whiteish (diff between r,g,b is small, and all are high)
        if abs(r - g) < 20 and abs(g - b) < 20 and r > 180 and g > 180 and b > 180:
            new_data.append((255, 255, 255, 0)) # transparent
        else:
            new_data.append(item)
            
    img.putdata(new_data)
    img.save(output_path, "PNG")

if __name__ == "__main__":
    remove_background(
        r"d:\Projects\Assitance\frontend\public\brand\logo.png",
        r"d:\Projects\Assitance\frontend\public\brand\logo_transparent.png"
    )
