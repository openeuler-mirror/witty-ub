#include "urma_failure_571.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure571> g_urma("urma_571");

bool UrmaFailure571::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'bdp_r_v2p_token_id_del_idx_lockless' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Failed to find node, index:')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure571::GetName() const
{
    return "bdp_r_v2p_token_id_del_idx_lockless 执行处理 token_id 失败导致当前资源状态无法推进";
}

std::string UrmaFailure571::GetRootCauseDesc() const
{
    return "bdp_r_v2p_token_id_del_idx_lockless 调用下层 provider、bond 组件或系统接口处理 token_id "
           "时返回失败，当前分支携带 ret/errno "
           "等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。";
}

RootCause UrmaFailure571::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure571::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure571::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Failed to find node, index";
}

std::string UrmaFailure571::GetId() const
{
    return "urma_571";
}

} // namespace diag
