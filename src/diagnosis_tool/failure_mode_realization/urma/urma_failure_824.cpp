#include "urma_failure_824.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure824> g_urma("urma_824");

bool UrmaFailure824::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_set_jfr_opt' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Failed to exec ops->set_jfr_opt.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure824::GetName() const
{
    return "设置JFR过程中依赖步骤失败";
}

std::string UrmaFailure824::GetRootCauseDesc() const
{
    return "函数用于设置JFR，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作"
           "失败。";
}

RootCause UrmaFailure824::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure824::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure824::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_set_jfr_opt，Failed to exec ops->set_jfr_opt.。";
}

std::string UrmaFailure824::GetId() const
{
    return "urma_824";
}

} // namespace diag
