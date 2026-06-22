#include "urma_failure_014.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure014> g_urma("urma_014");

bool UrmaFailure014::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_import_jetty") != std::string::npos &&
           message.find("Failed to init target active indices") != std::string::npos;
}

std::string UrmaFailure014::GetName() const
{
    return "下层查询返回失败导致导入Jetty失败";
}

std::string UrmaFailure014::GetRootCauseDesc() const
{
    return "bondp_import_jetty需要从provider、驱动或缓存中获取Jetty状态，查询结果失败会导致调用方无法取得有效信息。";
}

RootCause UrmaFailure014::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure014::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure014::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_import_jetty，Failed to init target active indices。";
}

std::string UrmaFailure014::GetId() const
{
    return "urma_014";
}
} // namespace diag
