#include "urma_failure_068.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure068> g_urma("urma_068");

bool UrmaFailure068::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_relink_primary_import") != std::string::npos &&
           message.find("Failed to unimport old primary ptjetty, lidx:") != std::string::npos &&
           message.find("tidx:") != std::string::npos;
}

std::string UrmaFailure068::GetName() const
{
    return "下层注册或导入返回失败导致导入relink、primary失败";
}

std::string UrmaFailure068::GetRootCauseDesc() const
{
    return "bondp_relink_primary_"
           "import在导入relink、primary时需要将对象登记到驱动或远端上下文，下层返回失败会阻断资源可见性建立。";
}

RootCause UrmaFailure068::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure068::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure068::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_relink_primary_import，Failed to unimport old primary ptjetty, "
           "lidx:，tid"
           "x:。";
}

std::string UrmaFailure068::GetId() const
{
    return "urma_068";
}
} // namespace diag
