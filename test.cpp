# include <iostream>
#include <stack>

using namespace std;
int main(){

// int arr[7] ;
// arr[1]= 100;
// arr[2] = 80;
// arr[3] = 60;
// arr[4] = 70;
// // 60,75,85;

// int n = -1;
// for (int i = 0 ; i<7 ; i++){
//     for (int j = 0 ; j <=i ; j++){

//     }
// }
    int arr [] = {100,80,60,70,60,75,85};

    stack <int> st ;
    for (int i = 0 ; i<7 ; i++){
        while(!st.empty() && st.top() <= arr[i]){
            st.pop();
            if (st.empty()){
                cout << -1 <<" ";
            }else {
            cout << st.top();
            }
            st.push(arr[i]);
        }
    }
    return 0 ;
}

