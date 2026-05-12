#include "urma_0833_urma_set_jfr_opt_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0833UrmaSetJfrOptFunctionFailure> g_urma("urma_0833");

bool Urma0833UrmaSetJfrOptFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0834", "urma_0835", "urma_0836", "urma_0837"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0833UrmaSetJfrOptFunctionFailure::GetName() const
{
    return "urma_set_jfr_opt 函数故障";
}

std::string Urma0833UrmaSetJfrOptFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0833UrmaSetJfrOptFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0833UrmaSetJfrOptFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0833UrmaSetJfrOptFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0833UrmaSetJfrOptFunctionFailure::GetId() const
{
    return "urma_0833";
}
} // namespace diag
