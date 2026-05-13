#include "urma_1033_urma_alloc_token_id_ex_dev_not_support_token_id.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1033UrmaAllocTokenIdExDevNotSupportTokenId> g_urma("urma_1033");

bool Urma1033UrmaAllocTokenIdExDevNotSupportTokenId::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"dev not support token id table mode."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1033UrmaAllocTokenIdExDevNotSupportTokenId::GetName() const
{
    return "urma_alloc_token_id_ex dev not support token id table mode.";
}

std::string Urma1033UrmaAllocTokenIdExDevNotSupportTokenId::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `flag.bs.multi_seg == 1 && dev_attr.dev_cap.feature.bs.muti_seg_per_token_id == "
           "0`；该路径返回 NULL";
}

RootCause Urma1033UrmaAllocTokenIdExDevNotSupportTokenId::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1033UrmaAllocTokenIdExDevNotSupportTokenId::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1033UrmaAllocTokenIdExDevNotSupportTokenId::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：dev not support token id table mode.";
}

std::string Urma1033UrmaAllocTokenIdExDevNotSupportTokenId::GetId() const
{
    return "urma_1033";
}
} // namespace diag
