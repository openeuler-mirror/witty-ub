#include "urma_failure_333.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure333> g_urma("urma_333");

bool UrmaFailure333::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'bdp_r_v2p_token_id_del_idx_lockless' "
                                    "\"$URMA_LOG_PATH\" 2>/dev/null | grep -F 'Failed to find node, index:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure333::GetName() const
{
    return "未找到可用于释放Token的有效对象或路由";
}

std::string UrmaFailure333::GetRootCauseDesc() const
{
    return "函数在释放Token过程中需要查找已建立的资源、端口或路由映射，但当前表项缺失或状态不可用，导致后续操作无法定位"
           "目标。";
}

RootCause UrmaFailure333::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure333::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure333::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bdp_r_v2p_token_id_del_idx_lockless，Failed to find node, index:。";
}

std::string UrmaFailure333::GetId() const
{
    return "urma_333";
}

} // namespace diag
