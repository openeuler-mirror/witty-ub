#include "urma_0924_get_topo_info_from_ko_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0924GetTopoInfoFromKoFunctionFailure> g_urma("urma_0924");

bool Urma0924GetTopoInfoFromKoFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0925", "urma_0926"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0924GetTopoInfoFromKoFunctionFailure::GetName() const
{
    return "get_topo_info_from_ko 函数故障";
}

std::string Urma0924GetTopoInfoFromKoFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0924GetTopoInfoFromKoFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0924GetTopoInfoFromKoFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0924GetTopoInfoFromKoFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0924GetTopoInfoFromKoFunctionFailure::GetId() const
{
    return "urma_0924";
}
} // namespace diag
