#include "urma_0179_bondp_query_jfr_query_pjfr_fail_index_ret.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0179BondpQueryJfrQueryPjfrFailIndexRet> g_urma("urma_0179");

bool Urma0179BondpQueryJfrQueryPjfrFailIndexRet::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"query pjfr fail, index:%, ret:%"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0179BondpQueryJfrQueryPjfrFailIndexRet::GetName() const
{
    return "bondp_query_jfr query pjfr fail, index:%, ret:%";
}

std::string Urma0179BondpQueryJfrQueryPjfrFailIndexRet::GetRootCauseDesc() const
{
    return "源码在该错误分支记录 URMA_LOG_ERR，通常表示当前函数检测到参数、状态、资源或下游返回值异常；该路径返回 ret";
}

RootCause Urma0179BondpQueryJfrQueryPjfrFailIndexRet::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0179BondpQueryJfrQueryPjfrFailIndexRet::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0179BondpQueryJfrQueryPjfrFailIndexRet::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：query pjfr fail, index:%, ret:%";
}

std::string Urma0179BondpQueryJfrQueryPjfrFailIndexRet::GetId() const
{
    return "urma_0179";
}
} // namespace diag
