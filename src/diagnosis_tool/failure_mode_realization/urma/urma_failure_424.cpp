#include "urma_failure_424.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure424> g_urma("urma_424");

bool UrmaFailure424::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_delete_pcontext' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Failed to get topo info, change to general mode'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure424::GetName() const
{
    return "获取健康检查过程中依赖步骤失败";
}

std::string UrmaFailure424::GetRootCauseDesc() const
{
    return "函数用于获取健康检查，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URM"
           "A操作失败。";
}

RootCause UrmaFailure424::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure424::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure424::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_delete_pcontext，Failed to get topo info, change to general "
           "mode。";
}

std::string UrmaFailure424::GetId() const
{
    return "urma_424";
}

} // namespace diag
