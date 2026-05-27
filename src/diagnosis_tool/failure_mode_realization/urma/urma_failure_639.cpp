#include "urma_failure_639.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure639> g_urma("urma_639");

bool UrmaFailure639::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_delete_jfc_batch' "
                                    "\"$URMA_LOG_PATH\" 2>/dev/null | grep -F 'Invalid parameter, index:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure639::GetName() const
{
    return "URMA context无效导致删除JFC失败";
}

std::string UrmaFailure639::GetRootCauseDesc() const
{
    return "函数用于删除JFC，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure639::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure639::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure639::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_delete_jfc_batch，Invalid parameter, index:。";
}

std::string UrmaFailure639::GetId() const
{
    return "urma_639";
}

} // namespace diag
