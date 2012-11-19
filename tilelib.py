# George Pantazopoulos
# Tile Library functions.

from math import ceil, floor

# -----------------------------------------------------------------------------

def genStartAndEndCoords(w, N):
    	sc = []
	ec = []
	for x in range(N):
		tw = float(w)/float(N)
		sc.append(int(1 + ceil((x * tw))))
			
	#print "sc:"
	#print sc

	for x in range(N):
		tw = float(w)/float(N)
		if x<N-1:
			ec.append((sc[x+1]-1))
		elif x==N-1:
			ec.append(w)
		else:
			raise "x==N"
		
	#print "ec:"
	#print ec
	return sc,ec

# -----------------------------------------------------------------------------

def MakeTileGrid(width, height, NX, NY):

	#tiles = []
        tilegrid = [[0 for i in range(NX)] for i in range(NY)]	
	
        sc_ec = genStartAndEndCoords(width, NX)
	sc = sc_ec[0]
	ec = sc_ec[1]

        sr_er = genStartAndEndCoords(height, NY)
        sr = sr_er[0]
        er = sr_er[1]

        tid = 1

        for y in range(NY):
            
            for x in range(NX):
                tile = {} 
                tile['id'] = tid
                tile['sc'] = sc[x]
                tile['ec'] = ec[x]
                tile['sr'] = sr[y]
                tile['er'] = er[y]

                tid += 1
                #tiles.append(tile)
                tilegrid[y][x] = tile
                
        return tilegrid

# -----------------------------------------------------------------------------

def MakeSpiralTileList(NX, NY, tilegrid):
    ordered_tiles = []
    
    x = 0
    y = 0

    num_rl = NX
    num_du = NY-1


    total_tiles = NX*NY

    while True:

        # if we try to move, and we can't, then we're done
        if num_rl == 0:
            break

        # Repeatedly pop and move right. The last move is down.
        for r in range(num_rl):   
            ordered_tiles.append(tilegrid[y][x])
            if r < (num_rl - 1):
                x += 1 # move right
            else:
                y += 1 # move down (once, after appending the last tile)

        # Next time move one fewer in the left-right direction.
        num_rl -= 1

        # if we try to move, and we can't, then we're done
        if num_du == 0:
            break

        # Repeatedly pop and move down. On the last move, go left
        for d in range(num_du):
            ordered_tiles.append(tilegrid[y][x])
            if d < (num_du - 1):
                y += 1 # move down
            else:
                x -= 1 # move left (once, after appending the last tile)

        # Next time, move one fewer in the up-down direction.
        num_du -= 1

        if num_rl == 0:
            break
        
        # Repeatedly pop and move left. On the last move, go up.
        for l in range(num_rl):  
            ordered_tiles.append(tilegrid[y][x])
            if l < (num_rl - 1):
                x -= 1 # move left
            else:
                y -= 1 # move up (once, after appending the last tile)

        num_rl -= 1

        if num_du == 0:
            break
        
        # Repeatedly pop and move up. On the last move, go right.
        for u in range(num_du):
            ordered_tiles.append(tilegrid[y][x])
            if u < (num_du - 1):
                y -= 1 # move up
            else:
                x += 1 # move right (once, after appending the last tile)

        num_du -= 1

        #print "num_du: " + str(num_du) + " " + "num_rl: " + str(num_rl)

    return ordered_tiles  

# -----------------------------------------------------------------------------
