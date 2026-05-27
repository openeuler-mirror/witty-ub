#include "urma_failure_771.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure771> g_urma("urma_771");

bool UrmaFailure771::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_check_trans_mode_valid' \"$URMA_LOG_PATH\" 2>/dev/null | grep -F "
        "'jfc cfg depth of range, depth:' | grep -F ', max_depth:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure771::GetName() const
{
    return "创建JFC过程中依赖步骤失败";
}

std::string UrmaFailure771::GetRootCauseDesc() const
{
    return "函数用于创建JFC，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作"
           "失败。";
}

RootCause UrmaFailure771::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure771::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure771::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_check_trans_mode_valid，jfc cfg depth of range, depth:，, "
           "max_depth:。";
}

std::string UrmaFailure771::GetId() const
{
    return "urma_771";
}

} // namespace diag
