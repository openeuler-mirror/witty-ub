#include "urma_failure_063.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure063> g_urma("urma_063");

bool UrmaFailure063::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_import_jfr") != std::string::npos &&
           message.find("Failed to import vjetty, []:") != std::string::npos;
}

std::string UrmaFailure063::GetName() const
{
    return "下层注册或导入返回失败导致导入JFR失败";
}

std::string UrmaFailure063::GetRootCauseDesc() const
{
    return "bondp_import_jfr在导入JFR时需要将对象登记到驱动或远端上下文，下层返回失败会阻断资源可见性建立。";
}

RootCause UrmaFailure063::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure063::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure063::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_import_jfr，Failed to import vjetty, []:。";
}

std::string UrmaFailure063::GetId() const
{
    return "urma_063";
}
} // namespace diag
