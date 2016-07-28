#install.packages("pdftools")
#install.packages("readxl")
library(pdftools)
library(readxl)

mkcsv = function(x){
  # parse the columns by at least two spaces
  tm = gsub("[ ]{2,}",",",x)
  if (length(unlist(strsplit(tm,","))) < 6){
    # correct for rows that missed the correct parsing (at least one per page)
    tm = gsub(' (?=[^ ]+$)',",",tm, perl=TRUE)
  }
  tm
}

# Bring in passwrd data
rrfile = "/path/to/user/data/file.xlsx"
rr = read_excel(rrfile,col_names=c("name","pass","date"),skip=2,col_types=rep("text",3))

d = "/path/to/user/statements/directory/"
ff = list.files(d)

for (f in ff){
  nn = gsub(".[^.]*$","",f)
  fi = pdf_text(paste0(d,f),upw=rr$pass[rr$name==nn])

  lines=c()
  for (p in 1:length(fi)){
    inp = gsub(",","",fi[p])  # get rid of commas
    ll = strsplit(inp,"\n")   # split on lines
    ll = lapply(ll,grep,pattern="^[A-Z0-9]{10}\\s",value=TRUE)[[1]] # Find transactions
    xx = unlist(lapply(ll,mkcsv))
    lines = c(lines,xx)
  }

  fileConn = file(paste0("/output/directory/for/data/",nn,".csv"))
  write(paste(lines,collapse="\n"),fileConn)
  close(fileConn)
}
