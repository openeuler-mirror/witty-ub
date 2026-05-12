#include "urma_0101_bondp_create_jfr_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0101BondpCreateJfrFunctionFailure> g_urma("urma_0101");

bool Urma0101BondpCreateJfrFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0102", "urma_0103", "urma_0104"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0101BondpCreateJfrFunctionFailure::GetName() const
{
    return "bondp_create_jfr 函数故障";
}

std::string Urma0101BondpCreateJfrFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0101BondpCreateJfrFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0101BondpCreateJfrFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0101BondpCreateJfrFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0101BondpCreateJfrFunctionFailure::GetId() const
{
    return "urma_0101";
}
} // namespace diag
