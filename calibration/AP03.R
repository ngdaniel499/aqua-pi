library(ggplot2)
library(MASS)
library(readxl)
AP03 <- read_excel("C:\\Users\\ngdan\\Documents\\WhaleX\\AquaPi\\aqua-pi\\calibration\\calibration_sheet.xlsx",
                   sheet = "Linear_AP03")

# Basic ggplot



ggplot(AP03, aes(x = Concentration, y = ChlCal)) +
  geom_point(color = "orange", size = 3) +
  geom_smooth(method = "rlm") +
  xlim(0,50)+
  ylim(0,3)+
  geom_errorbar(aes(ymin = ChlCal - ChlCalRangeCI,        # Lower limit: Value - Range
                    ymax = ChlCal + ChlCalRangeCI),       # Upper limit: Value + Range
                width = 1,                     # Width of error bar caps
                color = "black") + 
    labs(title = "Nicely Formatted Plot",
       subtitle = "Data imported from Excel",
       x = "Concentration",
       y = "ChlCal") +
  theme_minimal(base_size = 14) +  # Larger base font size
  theme(
    plot.title = element_text(hjust = 0.5, face = "bold", size = 18),
    plot.subtitle = element_text(hjust = 0.5, size = 12)
  ) # Customize x-axis ticks




    