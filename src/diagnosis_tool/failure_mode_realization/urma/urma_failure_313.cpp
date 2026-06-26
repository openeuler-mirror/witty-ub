#include "urma_failure_313.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure313> g_urma("urma_313");

bool UrmaFailure313::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_create_vseg") != std::string::npos &&
           message.find("Fail to register vseg, ret:") != std::string::npos;
}

std::string UrmaFailure313::GetName() const
{
    return "下层注册或导入返回失败导致创建VSEG失败";
}

std::string UrmaFailure313::GetRootCauseDesc() const
{
    return "bondp_create_vseg在创建VSEG时需要将对象登记到驱动或远端上下文，下层返回失败会阻断资源可见性建立。";
}

RootCause UrmaFailure313::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure313::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure313::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_create_vseg，Fail to register vseg, ret:。";
}

std::string UrmaFailure313::GetId() const
{
    return "urma_313";
}
} // namespace diag
