#include "urma_failure_748.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure748> g_urma("urma_748");

bool UrmaFailure748::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("check_valid_sgl") != std::string::npos &&
           message.find("sge is a null pointer.") != std::string::npos;
}

std::string UrmaFailure748::GetName() const
{
    return "valid、SGL状态不满足要求导致校验valid、SGL失败";
}

std::string UrmaFailure748::GetRootCauseDesc() const
{
    return "check_valid_sgl执行校验valid、SGL时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure748::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure748::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure748::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：check_valid_sgl，sge is a null pointer.。";
}

std::string UrmaFailure748::GetId() const
{
    return "urma_748";
}
} // namespace diag
