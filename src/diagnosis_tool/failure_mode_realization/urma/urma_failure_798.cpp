#include "urma_failure_798.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure798> g_urma("urma_798");

bool UrmaFailure798::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_set_jfs_opt' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Failed to exec urma_jfr_set_options.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure798::GetName() const
{
    return "设置JFR过程中依赖步骤失败";
}

std::string UrmaFailure798::GetRootCauseDesc() const
{
    return "函数用于设置JFR，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作"
           "失败。";
}

RootCause UrmaFailure798::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure798::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure798::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_set_jfs_opt，Failed to exec urma_jfr_set_options.。";
}

std::string UrmaFailure798::GetId() const
{
    return "urma_798";
}

} // namespace diag
