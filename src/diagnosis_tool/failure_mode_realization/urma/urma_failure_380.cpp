#include "urma_failure_380.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure380> g_urma("urma_380");

bool UrmaFailure380::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("post_send_check_valid") != std::string::npos &&
           message.find("Invalid src_chip_id:") != std::string::npos;
}

std::string UrmaFailure380::GetName() const
{
    return "valid状态不满足要求导致投递valid失败";
}

std::string UrmaFailure380::GetRootCauseDesc() const
{
    return "post_send_check_valid执行投递valid时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure380::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure380::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure380::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：post_send_check_valid，Invalid src_chip_id:。";
}

std::string UrmaFailure380::GetId() const
{
    return "urma_380";
}
} // namespace diag
