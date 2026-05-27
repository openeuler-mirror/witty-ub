#include "urma_failure_636.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure636> g_urma("urma_636");

bool UrmaFailure636::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_delete_jfc_batch' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'bad jfc index exceed array length, bad_jfc_index:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure636::GetName() const
{
    return "删除JFC过程中依赖步骤失败";
}

std::string UrmaFailure636::GetRootCauseDesc() const
{
    return "函数用于删除JFC，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作"
           "失败。";
}

RootCause UrmaFailure636::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure636::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure636::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_cmd_delete_jfc_batch，bad jfc index exceed array length, bad_jfc_index:";
}

std::string UrmaFailure636::GetId() const
{
    return "urma_636";
}

} // namespace diag
