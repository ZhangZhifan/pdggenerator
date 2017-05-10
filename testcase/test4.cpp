int main() {
    int a = 0;
    int b = 0;
    int d[10] = {0};
    int c = d[b[0]];
    int e[10] = {0};
    
    while (b < 10) {
        if (b % 2) {
            scanf("%d", &a);
        }
        else
            a = a - 1;
        b = b + 1;
    }
    
    for (a = 0, b = 1, c[0] = 0; a < 10; a = a + 1, b = b+1){
        if (a % 2)
            printf("%d ", a);
        else
            return 0;
        b += 2;
    }
}
