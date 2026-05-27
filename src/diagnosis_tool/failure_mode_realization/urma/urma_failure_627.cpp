#include "urma_failure_627.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure627> g_urma("urma_627");

bool UrmaFailure627::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_delete_jfr_batch' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'bad jfr index exceed array length, bad_jfr_index:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure627::GetName() const
{
    return "删除JFR过程中依赖步骤失败";
}

std::string UrmaFailure627::GetRootCauseDesc() const
{
    return "函数用于删除JFR，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作"
           "失败。";
}

RootCause UrmaFailure627::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure627::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure627::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_cmd_delete_jfr_batch，bad jfr index exceed array length, bad_jfr_index:";
}

std::string UrmaFailure627::GetId() const
{
    return "urma_627";
}

} // namespace diag
