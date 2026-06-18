#include "urma_failure_020.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure020> g_urma("urma_020");

bool UrmaFailure020::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_provider_bond_init") != std::string::npos &&
           message.find("Provider Bond register ops failed.") != std::string::npos;
}

std::string UrmaFailure020::GetName() const
{
    return "下层注册或导入返回失败导致初始化provider、Bond资源失败";
}

std::string UrmaFailure020::GetRootCauseDesc() const
{
    return "urma_provider_bond_"
           "init在初始化provider、Bond资源时需要将对象登记到驱动或远端上下文，下层返回失败会阻断资源可见性建立。";
}

RootCause UrmaFailure020::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure020::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure020::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_provider_bond_init，Provider Bond register ops failed.。";
}

std::string UrmaFailure020::GetId() const
{
    return "urma_020";
}
} // namespace diag
