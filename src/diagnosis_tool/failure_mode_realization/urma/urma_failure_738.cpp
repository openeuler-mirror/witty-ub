#include "urma_failure_738.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure738> g_urma("urma_738");

bool UrmaFailure738::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_set_jfs_opt' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'jfc not exist in jfs.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure738::GetName() const
{
    return "设置JFC过程中依赖步骤失败";
}

std::string UrmaFailure738::GetRootCauseDesc() const
{
    return "函数用于设置JFC，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作"
           "失败。";
}

RootCause UrmaFailure738::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure738::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure738::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_cmd_set_jfs_opt，jfc not exist in jfs.";
}

std::string UrmaFailure738::GetId() const
{
    return "urma_738";
}

} // namespace diag
