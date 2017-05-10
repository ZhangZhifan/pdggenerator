int main() {
    int a = 0;
    int b = 0;
    while (b < 10) {
        if (b % 2)
            continue;
        b = b + 1;
        a = a + 2;
    }
}
