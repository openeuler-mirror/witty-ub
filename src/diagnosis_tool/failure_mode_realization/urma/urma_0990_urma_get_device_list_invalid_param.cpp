#include "urma_0990_urma_get_device_list_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0990UrmaGetDeviceListInvalidParam> g_urma("urma_0990");

bool Urma0990UrmaGetDeviceListInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0990UrmaGetDeviceListInvalidParam::GetName() const
{
    return "urma_get_device_list 参数非法";
}

std::string Urma0990UrmaGetDeviceListInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `num_devices == NULL`；该路径返回 NULL";
}

RootCause Urma0990UrmaGetDeviceListInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0990UrmaGetDeviceListInvalidParam::GetFixSuggDesc() const
{
    return "```\nlsmod | grep udma\nurma_admin show -a // 查看UB设备是否存在，部署完成后重试\n```";
}

std::string Urma0990UrmaGetDeviceListInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0990UrmaGetDeviceListInvalidParam::GetId() const
{
    return "urma_0990";
}
} // namespace diag
