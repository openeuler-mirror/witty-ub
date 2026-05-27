#include "urma_failure_024.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure024> g_urma("urma_024");

bool UrmaFailure024::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_init' \"$URMA_LOG_PATH\" 2>/dev/null "
                                    "| grep -F 'Failed to init bondp netlink context.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure024::GetName() const
{
    return "初始化context过程中依赖步骤失败";
}

std::string UrmaFailure024::GetRootCauseDesc() const
{
    return "函数用于初始化context，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次UR"
           "MA操作失败。";
}

RootCause UrmaFailure024::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure024::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure024::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_init，Failed to init bondp netlink context.。";
}

std::string UrmaFailure024::GetId() const
{
    return "urma_024";
}

} // namespace diag
