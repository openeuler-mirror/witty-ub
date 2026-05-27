#include "urma_failure_650.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure650> g_urma("urma_650");

bool UrmaFailure650::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_free_jfc' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'jfc still actived, please deactived first'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure650::GetName() const
{
    return "释放JFC过程中依赖步骤失败";
}

std::string UrmaFailure650::GetRootCauseDesc() const
{
    return "函数用于释放JFC，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作"
           "失败。";
}

RootCause UrmaFailure650::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure650::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure650::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_free_jfc，jfc still actived, please deactived first。";
}

std::string UrmaFailure650::GetId() const
{
    return "urma_650";
}

} // namespace diag
