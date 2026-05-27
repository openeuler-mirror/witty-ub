#include "urma_failure_719.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure719> g_urma("urma_719");

bool UrmaFailure719::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_user_ctl' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Unsupported opcode, opcode:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure719::GetName() const
{
    return "设置context过程中依赖步骤失败";
}

std::string UrmaFailure719::GetRootCauseDesc() const
{
    return "函数用于设置context，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA"
           "操作失败。";
}

RootCause UrmaFailure719::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure719::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure719::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：bondp_user_ctl，Unsupported opcode, opcode:";
}

std::string UrmaFailure719::GetId() const
{
    return "urma_719";
}

} // namespace diag
