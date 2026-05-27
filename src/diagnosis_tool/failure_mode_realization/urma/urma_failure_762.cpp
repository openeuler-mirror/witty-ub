#include "urma_failure_762.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure762> g_urma("urma_762");

bool UrmaFailure762::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_check_trans_mode_valid' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'jfc cfg depth of range, depth:' | grep -F ', max_depth:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure762::GetName() const
{
    return "创建JFC过程中依赖步骤失败";
}

std::string UrmaFailure762::GetRootCauseDesc() const
{
    return "函数用于创建JFC，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作"
           "失败。";
}

RootCause UrmaFailure762::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure762::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure762::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_check_trans_mode_valid，jfc cfg depth of range, depth:，, max_depth:";
}

std::string UrmaFailure762::GetId() const
{
    return "urma_762";
}

} // namespace diag
