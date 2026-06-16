#include "urma_failure_616.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure616> g_urma("urma_616");

bool UrmaFailure616::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_delete_context' "
                                    "\"$URMA_LOG_PATH\" 2>/dev/null | grep -F 'Invalid parameter'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure616::GetName() const
{
    return "URMA context无效导致删除context失败";
}

std::string UrmaFailure616::GetRootCauseDesc() const
{
    return "函数用于删除context，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure616::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure616::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure616::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_delete_context，Invalid parameter。";
}

std::string UrmaFailure616::GetId() const
{
    return "urma_616";
}

} // namespace diag
