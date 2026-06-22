#include "urma_failure_227.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure227> g_urma("urma_227");

bool UrmaFailure227::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bdp_r_v2p_token_id_del_idx_lockless") != std::string::npos &&
           message.find("Failed to find node, index:") != std::string::npos;
}

std::string UrmaFailure227::GetName() const
{
    return "bdpBDP、R、V2P执行失败导致bdpBDP、R、V2P失败";
}

std::string UrmaFailure227::GetRootCauseDesc() const
{
    return "bdp_r_v2p_token_id_del_idx_"
           "lockless执行bdpBDP、R、V2P时依赖的bdpBDP、R、V2P步骤返回错误，当前URMA操作无法继续完成。";
}

RootCause UrmaFailure227::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure227::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure227::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bdp_r_v2p_token_id_del_idx_lockless，Failed to find node, index:。";
}

std::string UrmaFailure227::GetId() const
{
    return "urma_227";
}
} // namespace diag
