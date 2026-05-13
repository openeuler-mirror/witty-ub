#include "urma_0222_bondp_jfr_get_args_list_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0222BondpJfrGetArgsListFunctionFailure> g_urma("urma_0222");

bool Urma0222BondpJfrGetArgsListFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0223", "urma_0224"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0222BondpJfrGetArgsListFunctionFailure::GetName() const
{
    return "bondp_jfr_get_args_list 函数故障";
}

std::string Urma0222BondpJfrGetArgsListFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0222BondpJfrGetArgsListFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0222BondpJfrGetArgsListFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0222BondpJfrGetArgsListFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0222BondpJfrGetArgsListFunctionFailure::GetId() const
{
    return "urma_0222";
}
} // namespace diag
