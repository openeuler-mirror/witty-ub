#include "urma_failure_052.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure052> g_urma("urma_052");

bool UrmaFailure052::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_import_pjetty") != std::string::npos &&
           message.find("Failed to import tjetty") != std::string::npos;
}

std::string UrmaFailure052::GetName() const
{
    return "下层注册或导入返回失败导致导入pjetty失败";
}

std::string UrmaFailure052::GetRootCauseDesc() const
{
    return "bondp_import_pjetty在导入pjetty时需要将对象登记到驱动或远端上下文，下层返回失败会阻断资源可见性建立。";
}

RootCause UrmaFailure052::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string UrmaFailure052::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure052::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_import_pjetty，Failed to import tjetty。";
}

std::string UrmaFailure052::GetId() const
{
    return "urma_052";
}
} // namespace diag
