#include "urma_0866_urma_parse_rsvd_jetty_range_failure_255.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0866UrmaParseRsvdJettyRangeFailure255> g_urma("urma_0866");

bool Urma0866UrmaParseRsvdJettyRangeFailure255::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"parse rsvd jetty:% failed"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0866UrmaParseRsvdJettyRangeFailure255::GetName() const
{
    return "urma_parse_rsvd_jetty_range 解析失败（日志行255）";
}

std::string Urma0866UrmaParseRsvdJettyRangeFailure255::GetRootCauseDesc() const
{
    return "解析设备属性、EID、sysfs 字段或输入格式失败，通常表示输入/设备上报内容不符合预期";
}

RootCause Urma0866UrmaParseRsvdJettyRangeFailure255::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0866UrmaParseRsvdJettyRangeFailure255::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0866UrmaParseRsvdJettyRangeFailure255::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：parse rsvd jetty:% failed";
}

std::string Urma0866UrmaParseRsvdJettyRangeFailure255::GetId() const
{
    return "urma_0866";
}
} // namespace diag
