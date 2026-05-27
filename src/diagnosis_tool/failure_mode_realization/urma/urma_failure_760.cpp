#include "urma_failure_760.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure760> g_urma("urma_760");

bool UrmaFailure760::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_set_jfr_opt' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'jfc not exist in jfr.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure760::GetName() const
{
    return "设置JFC过程中依赖步骤失败";
}

std::string UrmaFailure760::GetRootCauseDesc() const
{
    return "函数用于设置JFC，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作"
           "失败。";
}

RootCause UrmaFailure760::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure760::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure760::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_set_jfr_opt，jfc not exist in jfr.。";
}

std::string UrmaFailure760::GetId() const
{
    return "urma_760";
}

} // namespace diag
