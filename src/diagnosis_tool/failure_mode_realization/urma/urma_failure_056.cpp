#include "urma_failure_056.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure056> g_urma("urma_056");

bool UrmaFailure056::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_import_jetty") != std::string::npos &&
           message.find("Failed to import pjetty") != std::string::npos;
}

std::string UrmaFailure056::GetName() const
{
    return "下层注册或导入返回失败导致导入Jetty失败";
}

std::string UrmaFailure056::GetRootCauseDesc() const
{
    return "bondp_import_jetty在导入Jetty时需要将对象登记到驱动或远端上下文，下层返回失败会阻断资源可见性建立。";
}

RootCause UrmaFailure056::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure056::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure056::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_import_jetty，Failed to import pjetty。";
}

std::string UrmaFailure056::GetId() const
{
    return "urma_056";
}
} // namespace diag
