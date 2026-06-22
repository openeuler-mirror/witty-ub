#include "urma_failure_221.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure221> g_urma("urma_221");

bool UrmaFailure221::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_query_jfr") != std::string::npos &&
           message.find("query pjfr fail, index:") != std::string::npos && message.find(", ret:") != std::string::npos;
}

std::string UrmaFailure221::GetName() const
{
    return "下层查询返回失败导致查询JFR失败";
}

std::string UrmaFailure221::GetRootCauseDesc() const
{
    return "bondp_query_jfr需要从provider、驱动或缓存中获取JFR状态，查询结果失败会导致调用方无法取得有效信息。";
}

RootCause UrmaFailure221::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure221::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure221::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_query_jfr，query pjfr fail, index:，, ret:。";
}

std::string UrmaFailure221::GetId() const
{
    return "urma_221";
}
} // namespace diag
