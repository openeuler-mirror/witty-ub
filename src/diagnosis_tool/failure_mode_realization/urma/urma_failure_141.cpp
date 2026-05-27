#include "urma_failure_141.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure141> g_urma("urma_141");

bool UrmaFailure141::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_delete_jetty_batch' \"$URMA_LOG_PATH\" 2>/dev/null | grep -F "
        "'bad jetty index exceed array length, bad_jetty_index:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure141::GetName() const
{
    return "删除Jetty过程中依赖步骤失败";
}

std::string UrmaFailure141::GetRootCauseDesc() const
{
    return "函数用于删除Jetty，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操"
           "作失败。";
}

RootCause UrmaFailure141::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure141::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure141::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_delete_jetty_batch，bad jetty index exceed array length, "
           "bad_jetty_index:。";
}

std::string UrmaFailure141::GetId() const
{
    return "urma_141";
}

} // namespace diag
