#include "urma_0334_delete_copied_jfr_wr_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0334DeleteCopiedJfrWrFunctionFailure> g_urma("urma_0334");

bool Urma0334DeleteCopiedJfrWrFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0335"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0334DeleteCopiedJfrWrFunctionFailure::GetName() const
{
    return "delete_copied_jfr_wr 函数故障";
}

std::string Urma0334DeleteCopiedJfrWrFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0334DeleteCopiedJfrWrFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0334DeleteCopiedJfrWrFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0334DeleteCopiedJfrWrFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0334DeleteCopiedJfrWrFunctionFailure::GetId() const
{
    return "urma_0334";
}
} // namespace diag
