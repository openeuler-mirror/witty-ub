#ifndef FAILURE_MODE_H
#define FAILURE_MODE_H
#pragma once

#include <memory>
#include <string>
#include <vector>
namespace diag {
class RootCause {
public:
    RootCause(bool isFinalRootCause_, std::string rootCause_)
        : isFinalRootCause(isFinalRootCause_),
          rootCause(rootCause_)
    {
    }
    bool GetIsFinalRootCause();
    std::string GetRootCause();

private:
    bool isFinalRootCause;
    std::string rootCause;
};

class FailureMode {
public:
    virtual void PrintDesc();
    virtual std::string GetName() const = 0;
    virtual std::string GetValidationMethodDesc() const = 0;
    virtual bool isValid() = 0;
    virtual std::string GetRootCauseDesc() const = 0;
    virtual RootCause AnalyzeRootCause();
    virtual std::string GetFixSuggDesc() const = 0;
    virtual std::string GetId() const = 0;
    void AddSubFailureMode(std::string faiureModeId);
    std::vector<std::string> GetSubFailureModes();

private:
    std::vector<std::string> subFailureModes;
};

} // namespace diag
#endif