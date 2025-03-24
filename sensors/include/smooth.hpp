#include <iostream>
using namespace std;

template<typename T, size_t window>
class Smooth {
public:
        Smooth() :
                initialized(false),
                index(0)
        { }

        void add(T addend) {
                if (!initialized) {
                        for (int idx = 0; idx < window; idx++) {
                                values[idx] = addend;
                        }
                        initialized = true;
                        total = window * addend;
                }
                total += addend - values[index];
                values[index] = addend;
                index++;
                index %= window;
        }

        T get () const {
                return total / window;
        }

private:

        friend ostream& operator << ( std::ostream& outs, const Smooth & s ) {
                return outs << "(index=" << s.index << ",total=" << s.total << ",average=" << s.get() << ")";
        }

        bool initialized;
        int index;
        T total;
        T values[window];
};
