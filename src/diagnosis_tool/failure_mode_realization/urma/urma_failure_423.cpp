#include "urma_failure_423.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure423> g_urma("urma_423");

bool UrmaFailure423::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'get_topo_info_from_ko' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Failed to get topo info, change to general mode'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure423::GetName() const
{
    return "获取context过程中依赖步骤失败";
}

std::string UrmaFailure423::GetRootCauseDesc() const
{
    return "函数用于获取context，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA"
           "操作失败。";
}

RootCause UrmaFailure423::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure423::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure423::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：get_topo_info_from_ko，Failed to get topo info, change to general "
           "mode。";
}

std::string UrmaFailure423::GetId() const
{
    return "urma_423";
}

} // namespace diag
