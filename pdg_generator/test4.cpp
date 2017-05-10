int main() {
    int a = 0;
    int b = 0;
    int d[10] = {0};
    int c = d[b];
    while (b < 10) {
        if (b % 2) {
            c = 2;
        }
        else
            a = a - 1;
        b = b + 1;
    }
    
    for (a = 0, b = 1, c[0] = 0; a < 10; a = a + 1){
        if (a % 2)
            b = 1;
        else
            return 0;
        b += 2;
    }
}
