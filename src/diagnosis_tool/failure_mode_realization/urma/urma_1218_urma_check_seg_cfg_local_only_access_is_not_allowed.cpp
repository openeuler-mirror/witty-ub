#include "urma_1218_urma_check_seg_cfg_local_only_access_is_not_allowed.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1218UrmaCheckSegCfgLocalOnlyAccessIsNotAllowed> g_urma("urma_1218");

bool Urma1218UrmaCheckSegCfgLocalOnlyAccessIsNotAllowed::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Local only access is not allowed to config with other accesses."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1218UrmaCheckSegCfgLocalOnlyAccessIsNotAllowed::GetName() const
{
    return "urma_check_seg_cfg Local only access is not allowed to";
}

std::string Urma1218UrmaCheckSegCfgLocalOnlyAccessIsNotAllowed::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `(seg_cfg->flag.bs.access & URMA_ACCESS_LOCAL_ONLY) && (seg_cfg->flag.bs.access & "
           "(URMA_ACCESS_READ |`；该路径返回 false";
}

RootCause Urma1218UrmaCheckSegCfgLocalOnlyAccessIsNotAllowed::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1218UrmaCheckSegCfgLocalOnlyAccessIsNotAllowed::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1218UrmaCheckSegCfgLocalOnlyAccessIsNotAllowed::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Local only access is not allowed to config with other accesses.";
}

std::string Urma1218UrmaCheckSegCfgLocalOnlyAccessIsNotAllowed::GetId() const
{
    return "urma_1218";
}
} // namespace diag
