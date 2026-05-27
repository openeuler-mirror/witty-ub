#include "urma_failure_536.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure536> g_urma("urma_536");

bool UrmaFailure536::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_check_seg_cfg' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'token_id must set when token_id_valid is true, or must NULL when token_id_valid is false.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure536::GetName() const
{
    return "设置Token过程中依赖步骤失败";
}

std::string UrmaFailure536::GetRootCauseDesc() const
{
    return "函数用于设置Token，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操"
           "作失败。";
}

RootCause UrmaFailure536::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure536::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure536::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_check_seg_cfg，token_id must set when token_id_valid is true, or must NULL "
           "when token_id_valid is false.";
}

std::string UrmaFailure536::GetId() const
{
    return "urma_536";
}

} // namespace diag
