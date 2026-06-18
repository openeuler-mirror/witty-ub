#include "urma_failure_054.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure054> g_urma("urma_054");

bool UrmaFailure054::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_import_jetty") != std::string::npos &&
           message.find("Failed to import vjetty, []:") != std::string::npos;
}

std::string UrmaFailure054::GetName() const
{
    return "下层注册或导入返回失败导致导入Jetty失败";
}

std::string UrmaFailure054::GetRootCauseDesc() const
{
    return "bondp_import_jetty在导入Jetty时需要将对象登记到驱动或远端上下文，下层返回失败会阻断资源可见性建立。";
}

RootCause UrmaFailure054::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure054::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure054::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_import_jetty，Failed to import vjetty, []:。";
}

std::string UrmaFailure054::GetId() const
{
    return "urma_054";
}
} // namespace diag
