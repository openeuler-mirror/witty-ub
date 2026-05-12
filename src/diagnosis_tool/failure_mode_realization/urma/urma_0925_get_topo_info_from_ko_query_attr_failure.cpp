#include "urma_0925_get_topo_info_from_ko_query_attr_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0925GetTopoInfoFromKoQueryAttrFailure> g_urma("urma_0925");

bool Urma0925GetTopoInfoFromKoQueryAttrFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to get topo info, change to general mode"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0925GetTopoInfoFromKoQueryAttrFailure::GetName() const
{
    return "get_topo_info_from_ko 查询属性失败";
}

std::string Urma0925GetTopoInfoFromKoQueryAttrFailure::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `urma_cmd_user_ctl(&bond_ctx->v_ctx, &in, &out, &data)`；该路径返回 -1";
}

RootCause Urma0925GetTopoInfoFromKoQueryAttrFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0925GetTopoInfoFromKoQueryAttrFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0925GetTopoInfoFromKoQueryAttrFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to get topo info, change to general mode";
}

std::string Urma0925GetTopoInfoFromKoQueryAttrFailure::GetId() const
{
    return "urma_0925";
}
} // namespace diag
