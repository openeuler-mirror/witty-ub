#include "urma_failure_366.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure366> g_urma("urma_366");

bool UrmaFailure366::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_create_jfs' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure366::GetName() const
{
    return "URMA context、JFS对象、目标Jetty对象无效导致创建JFS失败";
}

std::string UrmaFailure366::GetRootCauseDesc() const
{
    return "函数用于创建JFS，调用方传入的URMA "
           "context、JFS对象、目标Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure366::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure366::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure366::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_create_jfs，Invalid parameter。";
}

std::string UrmaFailure366::GetId() const
{
    return "urma_366";
}

} // namespace diag
